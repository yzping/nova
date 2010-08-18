# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
SQLAlchemy models for nova data
"""
import os

from sqlalchemy.orm import relationship, backref, validates, exc
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import MetaData, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

from nova import auth
from nova import exception
from nova import flags

FLAGS=flags.FLAGS

Base = declarative_base()

flags.DEFINE_string('sql_connection',
                    'sqlite:///%s/nova.sqlite' % os.path.abspath("./"),
                    'connection string for sql database')

class NovaBase(object):
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    _session = None
    _engine = None
    @classmethod
    def create_engine(cls):
        if NovaBase._engine is not None:
           return NovaBase._engine
        from sqlalchemy import create_engine
        NovaBase._engine = create_engine(FLAGS.sql_connection, echo=False)
        Base.metadata.create_all(NovaBase._engine)
        return NovaBase._engine

    @classmethod
    def get_session(cls):
        from sqlalchemy.orm import sessionmaker
        if NovaBase._session == None:
            NovaBase.create_engine()
            NovaBase._session = sessionmaker(bind=NovaBase._engine)()
        return NovaBase._session

    @classmethod
    def all(cls):
        session = NovaBase.get_session()
        return session.query(cls).all()

    @classmethod
    def count(cls):
        session = NovaBase.get_session()
        return session.query(cls).count()

    @classmethod
    def find(cls, obj_id):
        session = NovaBase.get_session()
        #print cls
        try:
            return session.query(cls).filter_by(id=obj_id).one()
        except exc.NoResultFound:
            raise exception.NotFound("No model for id %s" % obj_id)

    def save(self):
        session = NovaBase.get_session()
        session.add(self)
        session.commit()

    def delete(self):
        session = NovaBase.get_session()
        session.delete(self)
        session.flush()

    def refresh(self):
        session = NovaBase.get_session()
        session.refresh(self)

class Image(Base, NovaBase):
    __tablename__ = 'images'
    user_id = Column(String)#, ForeignKey('users.id'), nullable=False)
    project_id = Column(String)#, ForeignKey('projects.id'), nullable=False)

    id = Column(String, primary_key=True)
    image_type = Column(String)
    public = Column(Boolean, default=False)
    state = Column(String)
    location = Column(String)
    arch = Column(String)
    default_kernel_id = Column(String)
    default_ramdisk_id = Column(String)

    @validates('image_type')
    def validate_image_type(self, key, image_type):
        assert(image_type in ['machine', 'kernel', 'ramdisk', 'raw'])

    @validates('state')
    def validate_state(self, key, state):
        assert(state in ['available', 'pending', 'disabled'])

    @validates('default_kernel_id')
    def validate_kernel_id(self, key, val):
        if val != 'machine':
            assert(val is None)

    @validates('default_ramdisk_id')
    def validate_ramdisk_id(self, key, val):
        if val != 'machine':
            assert(val is None)


class PhysicalNode(Base):
    __tablename__ = 'physical_nodes'
    id = Column(Integer, primary_key=True)

class Instance(Base, NovaBase):
    __tablename__ = 'instances'
    id = Column(Integer, primary_key=True)

    user_id = Column(String) #, ForeignKey('users.id'), nullable=False)
    project_id = Column(String) #, ForeignKey('projects.id'))

    @property
    def user(self):
        return auth.manager.AuthManager().get_user(self.user_id)

    @property
    def project(self):
        return auth.manager.AuthManager().get_project(self.project_id)

    # FIXME: make this opaque somehow
    @property
    def name(self):
        return "i-%s" % self.id


    image_id = Column(Integer, ForeignKey('images.id'), nullable=False)
    kernel_id = Column(String, ForeignKey('images.id'), nullable=True)
    ramdisk_id = Column(String, ForeignKey('images.id'), nullable=True)

    launch_index = Column(Integer)
    key_name = Column(String)
    key_data = Column(Text)
    security_group = Column(String)

    state = Column(Integer)
    state_description = Column(String)

    hostname = Column(String)
    physical_node_id = Column(Integer)

    instance_type = Column(Integer)

    user_data = Column(Text)

    reservation_id = Column(String)
    mac_address = Column(String)

    def set_state(self, state_code, state_description=None):
        from nova.compute import power_state
        self.state = state_code
        if not state_description:
            state_description = power_state.name(state_code)
        self.state_description = state_description
        self.save()

#    ramdisk = relationship(Ramdisk, backref=backref('instances', order_by=id))
#    kernel = relationship(Kernel, backref=backref('instances', order_by=id))
#    project = relationship(Project, backref=backref('instances', order_by=id))

#TODO - see Ewan's email about state improvements
    # vmstate_state = running, halted, suspended, paused
    # power_state = what we have
    # task_state = transitory and may trigger power state transition

    #@validates('state')
    #def validate_state(self, key, state):
    #    assert(state in ['nostate', 'running', 'blocked', 'paused', 'shutdown', 'shutoff', 'crashed'])

class Volume(Base, NovaBase):
    __tablename__ = 'volumes'
    id = Column(Integer, primary_key=True)
    volume_id = Column(String)

    user_id = Column(String) #, ForeignKey('users.id'), nullable=False)
    project_id = Column(String) #, ForeignKey('projects.id'))

    # FIXME: should be physical_node_id = Column(Integer)
    node_name = Column(String)
    size = Column(Integer)
    alvailability_zone = Column(String) # FIXME foreign key?
    instance_id = Column(Integer, ForeignKey('instances.id'), nullable=True)
    mountpoint = Column(String)
    attach_time = Column(String) # FIXME datetime
    status = Column(String) # FIXME enum?
    attach_status = Column(String) # FIXME enum

class ExportDevice(Base, NovaBase):
    __tablename__ = 'export_devices'
    id = Column(Integer, primary_key=True)
    shelf_id = Column(Integer)
    blade_id = Column(Integer)
    volume_id = Column(Integer, ForeignKey('volumes.id'), nullable=True)
    volume = relationship(Volume, backref=backref('export_device',
                                                  uselist=False))

class Network(Base, NovaBase):
    __tablename__ = 'networks'
    id = Column(Integer, primary_key=True)
    kind = Column(String)

    injected = Column(Boolean, default=False)
    network_str = Column(String)
    netmask = Column(String)
    bridge = Column(String)
    gateway = Column(String)
    broadcast = Column(String)
    dns = Column(String)

    vlan = Column(Integer)
    vpn_public_ip_str = Column(String)
    vpn_public_port = Column(Integer)
    vpn_private_ip_str = Column(String)

    project_id = Column(String) #, ForeignKey('projects.id'), nullable=False)
    # FIXME: should be physical_node_id = Column(Integer)
    node_name = Column(String)


class NetworkIndex(Base, NovaBase):
    __tablename__ = 'network_indexes'
    id = Column(Integer, primary_key=True)
    index = Column(Integer)
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=True)
    network = relationship(Network, backref=backref('network_index',
                                                      uselist=False))


#FIXME can these both come from the same baseclass?
class FixedIp(Base, NovaBase):
    __tablename__ = 'fixed_ips'
    id = Column(Integer, primary_key=True)
    ip_str = Column(String, unique=True)
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False)
    network = relationship(Network, backref=backref('fixed_ips'))
    instance_id = Column(Integer, ForeignKey('instances.id'), nullable=True)
    instance = relationship(Instance, backref=backref('fixed_ip',
                                                      uselist=False))
    allocated = Column(Boolean, default=False)
    leased = Column(Boolean, default=False)
    reserved = Column(Boolean, default=False)

    @classmethod
    def find_by_ip_str(cls, ip_str):
        session = NovaBase.get_session()
        try:
            return session.query(cls).filter_by(ip_str=ip_str).one()
        except exc.NoResultFound:
            raise exception.NotFound("No model for ip str %s" % ip_str)

class ElasticIp(Base, NovaBase):
    __tablename__ = 'elastic_ips'
    id = Column(Integer, primary_key=True)
    ip_str = Column(String, unique=True)
    fixed_ip_id = Column(Integer, ForeignKey('fixed_ips.id'), nullable=True)
    fixed_ip = relationship(FixedIp, backref=backref('elastic_ips'))

    project_id = Column(String) #, ForeignKey('projects.id'), nullable=False)
    # FIXME: should be physical_node_id = Column(Integer)
    node_name = Column(String)

    @classmethod
    def find_by_ip_str(cls, ip_str):
        session = NovaBase.get_session()
        try:
            return session.query(cls).filter_by(ip_str=ip_str).one()
        except exc.NoResultFound:
            raise exception.NotFound("No model for ip str %s" % ip_str)


def create_session(engine=None):
    return NovaBase.get_session()

if __name__ == '__main__':
    engine = NovaBase.create_engine()
    session = NovaBase.create_session(engine)

    instance = Instance(image_id='as', ramdisk_id='AS', user_id='anthony')
    user = User(id='anthony')
    session.add(instance)
    session.commit()

